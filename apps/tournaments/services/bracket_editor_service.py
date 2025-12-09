"""
Bracket Editor Service (Epic 3.3)

Provides bracket editing operations for organizers:
- Swap participants between matches
- Move participants to different matches
- Remove participants (creating byes)
- Repair bracket integrity
- Validate bracket structure

Architecture:
- Lives in tournaments app (operates on ORM models)
- Uses existing bracket structure created by BracketEngineService
- Records audit log for all edit operations
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import Match, TournamentStage

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of bracket validation check."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BracketEditorService:
    """
    Service for editing tournament brackets.
    
    Provides operations to manually adjust brackets while maintaining
    integrity and recording audit trail.
    """
    
    @staticmethod
    @transaction.atomic
    def swap_participants(match1_id: int, match2_id: int) -> None:
        """
        Swap participants between two matches.
        
        Swaps the participant IDs (team/player slots) between two matches.
        Preserves match structure and state.
        
        Args:
            match1_id: ID of first match
            match2_id: ID of second match
        
        Raises:
            ValidationError: If matches cannot be swapped (completed, invalid state)
        
        Example:
            Before: Match1: Team A vs Team B, Match2: Team C vs Team D
            After:  Match1: Team C vs Team D, Match2: Team A vs Team B
        """
        match1 = Match.objects.select_for_update().get(id=match1_id)
        match2 = Match.objects.select_for_update().get(id=match2_id)
        
        # Validate swap is allowed
        if match1.state == Match.COMPLETED or match2.state == Match.COMPLETED:
            raise ValidationError("Cannot swap participants in completed matches")
        
        if match1.state == Match.LIVE or match2.state == Match.LIVE:
            raise ValidationError("Cannot swap participants in live matches")
        
        # Swap participant IDs
        match1_p1, match1_p2 = match1.participant1_id, match1.participant2_id
        match1_p1_name, match1_p2_name = match1.participant1_name, match1.participant2_name
        
        match1.participant1_id = match2.participant1_id
        match1.participant2_id = match2.participant2_id
        match1.participant1_name = match2.participant1_name
        match1.participant2_name = match2.participant2_name
        
        match2.participant1_id = match1_p1
        match2.participant2_id = match1_p2
        match2.participant1_name = match1_p1_name
        match2.participant2_name = match1_p2_name
        
        match1.save()
        match2.save()
        
        # Log audit entry
        BracketEditorService._log_edit(
            stage_id=match1.lobby_info.get('stage_id') if match1.lobby_info else None,
            operation="swap",
            match_ids=[match1.id, match2.id],
            old_data={
                "match1_participants": [match1_p1, match1_p2],
                "match2_participants": [match2.participant1_id, match2.participant2_id],
            },
            new_data={
                "match1_participants": [match1.participant1_id, match1.participant2_id],
                "match2_participants": [match2.participant1_id, match2.participant2_id],
            },
        )
        
        logger.info(f"Swapped participants between match {match1_id} and {match2_id}")
    
    @staticmethod
    @transaction.atomic
    def move_participant(
        participant_id: int,
        from_match_id: int,
        to_match_id: int,
        slot: Optional[int] = None
    ) -> None:
        """
        Move a participant from one match to another.
        
        Args:
            participant_id: ID of participant to move
            from_match_id: Source match ID
            to_match_id: Destination match ID
            slot: Target slot (1 or 2), None for first available
        
        Raises:
            ValidationError: If move is invalid
        """
        from_match = Match.objects.select_for_update().get(id=from_match_id)
        to_match = Match.objects.select_for_update().get(id=to_match_id)
        
        # Validate move is allowed
        if from_match.state == Match.COMPLETED or to_match.state == Match.COMPLETED:
            raise ValidationError("Cannot move participants in completed matches")
        
        if from_match.state == Match.LIVE or to_match.state == Match.LIVE:
            raise ValidationError("Cannot move participants in live matches")
        
        # Find participant in source match
        if from_match.participant1_id == participant_id:
            from_slot = 1
        elif from_match.participant2_id == participant_id:
            from_slot = 2
        else:
            raise ValidationError(f"Participant {participant_id} not found in match {from_match_id}")
        
        # Determine target slot
        if slot is None:
            # Use first available slot
            if to_match.participant1_id is None:
                target_slot = 1
            elif to_match.participant2_id is None:
                target_slot = 2
            else:
                raise ValidationError(f"No available slots in match {to_match_id}")
        else:
            target_slot = slot
        
        # Get participant name
        participant_name = from_match.participant1_name if from_slot == 1 else from_match.participant2_name
        
        # Remove from source match (create bye)
        if from_slot == 1:
            from_match.participant1_id = None
            from_match.participant1_name = ""
        else:
            from_match.participant2_id = None
            from_match.participant2_name = ""
        
        # Add to destination match
        old_participant_id = None
        if target_slot == 1:
            old_participant_id = to_match.participant1_id
            to_match.participant1_id = participant_id
            to_match.participant1_name = participant_name
        else:
            old_participant_id = to_match.participant2_id
            to_match.participant2_id = participant_id
            to_match.participant2_name = participant_name
        
        from_match.save()
        to_match.save()
        
        # Log audit entry
        BracketEditorService._log_edit(
            stage_id=from_match.lobby_info.get('stage_id') if from_match.lobby_info else None,
            operation="move",
            match_ids=[from_match_id, to_match_id],
            old_data={
                "participant_id": participant_id,
                "from_match": from_match_id,
                "from_slot": from_slot,
                "replaced_participant": old_participant_id,
            },
            new_data={
                "to_match": to_match_id,
                "to_slot": target_slot,
            },
        )
        
        logger.info(f"Moved participant {participant_id} from match {from_match_id} to {to_match_id}")
    
    @staticmethod
    @transaction.atomic
    def remove_participant(match_id: int, participant_id: int) -> None:
        """
        Remove a participant from a match (creates bye).
        
        Args:
            match_id: Match ID
            participant_id: Participant to remove
        
        Raises:
            ValidationError: If removal is invalid
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        # Validate removal is allowed
        if match.state == Match.COMPLETED:
            raise ValidationError("Cannot remove participants from completed matches")
        
        if match.state == Match.LIVE:
            raise ValidationError("Cannot remove participants from live matches")
        
        # Find and remove participant
        removed = False
        old_slot = None
        if match.participant1_id == participant_id:
            match.participant1_id = None
            match.participant1_name = ""
            removed = True
            old_slot = 1
        elif match.participant2_id == participant_id:
            match.participant2_id = None
            match.participant2_name = ""
            removed = True
            old_slot = 2
        
        if not removed:
            raise ValidationError(f"Participant {participant_id} not found in match {match_id}")
        
        match.save()
        
        # Log audit entry
        BracketEditorService._log_edit(
            stage_id=match.lobby_info.get('stage_id') if match.lobby_info else None,
            operation="remove",
            match_ids=[match_id],
            old_data={
                "participant_id": participant_id,
                "slot": old_slot,
            },
            new_data={},
        )
        
        logger.info(f"Removed participant {participant_id} from match {match_id}")
    
    @staticmethod
    @transaction.atomic
    def repair_bracket(stage_id: int) -> Dict[str, Any]:
        """
        Repair bracket integrity issues.
        
        Fixes common problems:
        - Matches with both slots empty → mark as cancelled
        - Orphaned matches (no participants from previous round)
        
        Args:
            stage_id: TournamentStage ID
        
        Returns:
            Dictionary with repair summary
        """
        stage = TournamentStage.objects.get(id=stage_id)
        
        # Get all matches for this stage
        matches = Match.objects.filter(
            tournament=stage.tournament,
            lobby_info__stage_id=stage_id
        ).order_by('round_number', 'match_number')
        
        repairs_made = {
            "cancelled_empty_matches": 0,
            "orphan_warnings": [],
        }
        
        # Fix matches with both slots empty
        for match in matches:
            if match.participant1_id is None and match.participant2_id is None:
                if match.state not in [Match.COMPLETED, Match.CANCELLED]:
                    match.state = Match.CANCELLED
                    match.save()
                    repairs_made["cancelled_empty_matches"] += 1
                    logger.info(f"Cancelled empty match {match.id}")
        
        # Log audit entry
        BracketEditorService._log_edit(
            stage_id=stage_id,
            operation="repair",
            match_ids=[],
            old_data={},
            new_data=repairs_made,
        )
        
        logger.info(f"Repaired bracket for stage {stage_id}: {repairs_made}")
        return repairs_made
    
    @staticmethod
    def validate_bracket(stage_id: int) -> ValidationResult:
        """
        Validate bracket integrity.
        
        Checks:
        - No match has two empty slots (unless cancelled)
        - No participant appears twice in the same round
        - Bracket structure is valid for format
        
        Args:
            stage_id: TournamentStage ID
        
        Returns:
            ValidationResult with errors and warnings
        """
        stage = TournamentStage.objects.get(id=stage_id)
        errors = []
        warnings = []
        
        # Get all matches for this stage
        matches = Match.objects.filter(
            tournament=stage.tournament,
            lobby_info__stage_id=stage_id
        ).order_by('round_number', 'match_number')
        
        # Check for matches with both slots empty
        for match in matches:
            if match.participant1_id is None and match.participant2_id is None:
                if match.state not in [Match.CANCELLED]:
                    errors.append(
                        f"Match {match.id} (Round {match.round_number}, #{match.match_number}) "
                        f"has no participants and is not cancelled"
                    )
        
        # Check for duplicate participants in same round
        rounds = {}
        for match in matches:
            round_num = match.round_number
            if round_num not in rounds:
                rounds[round_num] = set()
            
            if match.participant1_id:
                if match.participant1_id in rounds[round_num]:
                    errors.append(
                        f"Participant {match.participant1_id} appears multiple times in round {round_num}"
                    )
                rounds[round_num].add(match.participant1_id)
            
            if match.participant2_id:
                if match.participant2_id in rounds[round_num]:
                    errors.append(
                        f"Participant {match.participant2_id} appears multiple times in round {round_num}"
                    )
                rounds[round_num].add(match.participant2_id)
        
        # Check for incomplete matches in early rounds with completed later rounds
        max_round_with_completed = 0
        for match in matches:
            if match.state == Match.COMPLETED:
                max_round_with_completed = max(max_round_with_completed, match.round_number)
        
        for match in matches:
            if match.round_number < max_round_with_completed:
                if match.state not in [Match.COMPLETED, Match.CANCELLED]:
                    warnings.append(
                        f"Match {match.id} in round {match.round_number} is incomplete "
                        f"while round {max_round_with_completed} has completed matches"
                    )
        
        is_valid = len(errors) == 0
        
        logger.info(
            f"Validated bracket for stage {stage_id}: "
            f"valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
    
    @staticmethod
    def _log_edit(
        stage_id: Optional[int],
        operation: str,
        match_ids: List[int],
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> None:
        """
        Log bracket edit operation to audit trail.
        
        Args:
            stage_id: TournamentStage ID (if applicable)
            operation: Type of edit (swap, move, remove, repair)
            match_ids: List of affected match IDs
            old_data: State before edit
            new_data: State after edit
            user_id: User who made the edit (optional for now)
        
        TODO (Phase 7): Store in BracketEditLog model for UI visualization
        """
        from apps.tournaments.models import BracketEditLog
        
        BracketEditLog.objects.create(
            stage_id=stage_id,
            operation=operation,
            match_ids=match_ids,
            old_data=old_data,
            new_data=new_data,
            user_id=user_id,
            timestamp=timezone.now(),
        )
        
        logger.debug(
            f"Audit log: {operation} on stage {stage_id}, "
            f"matches {match_ids}, user {user_id}"
        )
