"""
Match Scheduling Adapter - Phase 7, Epic 7.2

Adapter for match scheduling operations, hiding ORM layer from services.

Architecture:
- Method-level ORM imports only (no module-level imports)
- Returns DTOs only
- Handles batch operations atomically
- No business logic (pure data access)

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from apps.tournament_ops.dtos.scheduling import (
    MatchSchedulingItemDTO,
    SchedulingSlotDTO,
    SchedulingConflictDTO,
)


class MatchSchedulingAdapter:
    """
    Adapter for match scheduling data access.
    
    Provides methods for:
    - Retrieving matches requiring scheduling
    - Updating match schedules (single and bulk)
    - Fetching stage scheduling constraints
    - Detecting scheduling conflicts
    
    All methods return DTOs and hide ORM implementation.
    """
    
    def get_matches_requiring_scheduling(
        self,
        tournament_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        unscheduled_only: bool = False
    ) -> List[MatchSchedulingItemDTO]:
        """
        Retrieve matches that require scheduling.
        
        Args:
            tournament_id: Filter by tournament
            stage_id: Filter by stage
            unscheduled_only: Only return matches without scheduled_time
            
        Returns:
            List of MatchSchedulingItemDTO objects
        """
        from apps.tournaments.models import Match
        from django.db.models import Q
        
        query = Q()
        
        if tournament_id:
            query &= Q(tournament_id=tournament_id)
        
        if stage_id:
            query &= Q(stage_id=stage_id)
        
        if unscheduled_only:
            query &= Q(scheduled_time__isnull=True)
        
        # Only schedulable states
        query &= Q(state__in=['scheduled', 'pending'])
        
        matches = Match.objects.filter(query).select_related(
            'tournament',
            'stage',
            'participant1',
            'participant2'
        ).order_by('stage__start_date', 'round_number', 'match_number')
        
        results = []
        for match in matches:
            # Get estimated duration from game rules
            duration_minutes = self._get_match_duration(match)
            
            # Check for conflicts
            conflicts = self._detect_match_conflicts(match)
            
            dto = MatchSchedulingItemDTO(
                match_id=match.id,
                tournament_id=match.tournament_id,
                tournament_name=match.tournament.name,
                stage_id=match.stage_id,
                stage_name=match.stage.name,
                round_number=match.round_number,
                match_number=match.match_number,
                participant1_id=match.participant1_id,
                participant1_name=match.participant1.name if match.participant1 else None,
                participant2_id=match.participant2_id,
                participant2_name=match.participant2.name if match.participant2 else None,
                scheduled_time=match.scheduled_time,
                estimated_duration_minutes=duration_minutes,
                state=match.state,
                lobby_info=match.lobby_info or {},
                conflicts=conflicts,
                can_reschedule=match.state in ['scheduled', 'pending']
            )
            results.append(dto)
        
        return results
    
    def update_match_schedule(
        self,
        match_id: int,
        scheduled_time: datetime,
        assigned_by_user_id: int
    ) -> MatchSchedulingItemDTO:
        """
        Update a single match's scheduled time.
        
        Args:
            match_id: Match to update
            scheduled_time: New scheduled time
            assigned_by_user_id: User making the assignment
            
        Returns:
            Updated MatchSchedulingItemDTO
            
        Raises:
            ValueError: If match not found or not schedulable
        """
        from apps.tournaments.models import Match
        from django.core.exceptions import ObjectDoesNotExist
        
        try:
            match = Match.objects.select_related(
                'tournament',
                'stage',
                'participant1',
                'participant2'
            ).get(id=match_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        if match.state not in ['scheduled', 'pending']:
            raise ValueError(f"Match {match_id} cannot be rescheduled (state: {match.state})")
        
        # Update scheduled time
        match.scheduled_time = scheduled_time
        match.save(update_fields=['scheduled_time'])
        
        # Log audit trail
        self._log_scheduling_audit(match_id, scheduled_time, assigned_by_user_id)
        
        # Return updated DTO
        duration_minutes = self._get_match_duration(match)
        conflicts = self._detect_match_conflicts(match)
        
        return MatchSchedulingItemDTO(
            match_id=match.id,
            tournament_id=match.tournament_id,
            tournament_name=match.tournament.name,
            stage_id=match.stage_id,
            stage_name=match.stage.name,
            round_number=match.round_number,
            match_number=match.match_number,
            participant1_id=match.participant1_id,
            participant1_name=match.participant1.name if match.participant1 else None,
            participant2_id=match.participant2_id,
            participant2_name=match.participant2.name if match.participant2 else None,
            scheduled_time=match.scheduled_time,
            estimated_duration_minutes=duration_minutes,
            state=match.state,
            lobby_info=match.lobby_info or {},
            conflicts=conflicts,
            can_reschedule=True
        )
    
    def bulk_update_match_schedule(
        self,
        stage_id: int,
        time_delta_minutes: int,
        assigned_by_user_id: int
    ) -> Dict[str, Any]:
        """
        Bulk shift all scheduled matches in a stage by a time delta.
        
        Args:
            stage_id: Stage to shift matches in
            time_delta_minutes: Minutes to shift (positive or negative)
            assigned_by_user_id: User making the change
            
        Returns:
            Dict with keys:
                - shifted_count: Number of matches shifted
                - match_ids: List of shifted match IDs
        """
        from apps.tournaments.models import Match
        from django.db import transaction
        
        delta = timedelta(minutes=time_delta_minutes)
        
        with transaction.atomic():
            matches = Match.objects.filter(
                stage_id=stage_id,
                scheduled_time__isnull=False,
                state__in=['scheduled', 'pending']
            ).select_for_update()
            
            match_ids = []
            for match in matches:
                new_time = match.scheduled_time + delta
                match.scheduled_time = new_time
                match.save(update_fields=['scheduled_time'])
                
                # Log audit
                self._log_scheduling_audit(match.id, new_time, assigned_by_user_id)
                
                match_ids.append(match.id)
        
        return {
            'shifted_count': len(match_ids),
            'match_ids': match_ids
        }
    
    def get_stage_time_window(self, stage_id: int) -> Dict[str, Any]:
        """
        Get scheduling time window for a stage.
        
        Args:
            stage_id: Stage ID
            
        Returns:
            Dict with keys:
                - start_date: Stage start datetime
                - end_date: Stage end datetime
                - blackout_periods: List of (start, end) tuples
        """
        from apps.tournaments.models import TournamentStage
        from django.core.exceptions import ObjectDoesNotExist
        
        try:
            stage = TournamentStage.objects.get(id=stage_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Stage {stage_id} not found")
        
        # Get blackout periods from tournament config
        blackout_periods = []
        if hasattr(stage.tournament, 'scheduling_config'):
            config = stage.tournament.scheduling_config or {}
            blackout_periods = config.get('blackout_periods', [])
        
        return {
            'start_date': stage.start_date,
            'end_date': stage.end_date,
            'blackout_periods': blackout_periods
        }
    
    def get_game_match_duration(self, game_id: int) -> int:
        """
        Get estimated match duration for a game.
        
        Args:
            game_id: Game ID
            
        Returns:
            Duration in minutes
        """
        from apps.games.models import Game
        from django.core.exceptions import ObjectDoesNotExist
        
        try:
            game = Game.objects.get(id=game_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Game {game_id} not found")
        
        # Get from game rules config
        if hasattr(game, 'rules_config'):
            config = game.rules_config or {}
            return config.get('estimated_match_duration_minutes', 60)
        
        return 60  # Default 1 hour
    
    def get_conflicts_for_match(
        self,
        match_id: int,
        proposed_time: datetime,
        duration_minutes: int
    ) -> List[SchedulingConflictDTO]:
        """
        Detect conflicts for scheduling a match at a proposed time.
        
        Args:
            match_id: Match to check
            proposed_time: Proposed scheduled time
            duration_minutes: Match duration
            
        Returns:
            List of SchedulingConflictDTO objects (warnings, not errors)
        """
        from apps.tournaments.models import Match
        from django.core.exceptions import ObjectDoesNotExist
        
        try:
            match = Match.objects.select_related('participant1', 'participant2').get(id=match_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Match {match_id} not found")
        
        conflicts = []
        proposed_end = proposed_time + timedelta(minutes=duration_minutes)
        
        # Check for team conflicts (same team in overlapping matches)
        team_ids = []
        if match.participant1_id:
            team_ids.append(match.participant1_id)
        if match.participant2_id:
            team_ids.append(match.participant2_id)
        
        if team_ids:
            overlapping = Match.objects.filter(
                scheduled_time__isnull=False,
                state__in=['scheduled', 'pending', 'in_progress']
            ).exclude(id=match_id).select_related('participant1', 'participant2')
            
            for other_match in overlapping:
                other_end = other_match.scheduled_time + timedelta(minutes=duration_minutes)
                
                # Check time overlap
                if (proposed_time < other_end and proposed_end > other_match.scheduled_time):
                    # Check if same team
                    other_teams = []
                    if other_match.participant1_id:
                        other_teams.append(other_match.participant1_id)
                    if other_match.participant2_id:
                        other_teams.append(other_match.participant2_id)
                    
                    common_teams = set(team_ids) & set(other_teams)
                    if common_teams:
                        conflicts.append(SchedulingConflictDTO(
                            conflict_type='team_conflict',
                            severity='warning',
                            message=f"Team has overlapping match at {other_match.scheduled_time}",
                            affected_match_ids=[match_id, other_match.id],
                            suggested_resolution=f"Reschedule to avoid overlap with match {other_match.id}"
                        ))
        
        # Check for blackout periods
        stage_window = self.get_stage_time_window(match.stage_id)
        blackout_periods = stage_window.get('blackout_periods', [])
        
        for blackout in blackout_periods:
            blackout_start = blackout['start']
            blackout_end = blackout['end']
            
            if (proposed_time < blackout_end and proposed_end > blackout_start):
                conflicts.append(SchedulingConflictDTO(
                    conflict_type='blackout_period',
                    severity='warning',
                    message=f"Overlaps with blackout period {blackout_start} - {blackout_end}",
                    affected_match_ids=[match_id],
                    suggested_resolution="Choose a time outside the blackout period"
                ))
        
        return conflicts
    
    # Private helper methods
    
    def _get_match_duration(self, match) -> int:
        """Get estimated duration for a match."""
        try:
            return self.get_game_match_duration(match.tournament.game_id)
        except Exception:
            return 60  # Default fallback
    
    def _detect_match_conflicts(self, match) -> List[str]:
        """Detect conflicts for a match's current schedule."""
        if not match.scheduled_time:
            return []
        
        duration = self._get_match_duration(match)
        conflicts_dto = self.get_conflicts_for_match(
            match.id,
            match.scheduled_time,
            duration
        )
        
        return [c.message for c in conflicts_dto]
    
    def _log_scheduling_audit(
        self,
        match_id: int,
        scheduled_time: datetime,
        assigned_by_user_id: int
    ) -> None:
        """Log scheduling change to audit trail."""
        from apps.tournaments.models import MatchAuditLog
        
        try:
            MatchAuditLog.objects.create(
                match_id=match_id,
                action='schedule_updated',
                user_id=assigned_by_user_id,
                details={
                    'scheduled_time': scheduled_time.isoformat(),
                    'assigned_by': assigned_by_user_id
                }
            )
        except Exception:
            # Don't fail scheduling if audit logging fails
            pass
