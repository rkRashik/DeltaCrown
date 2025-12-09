"""
Match orchestration service.

This service manages match scheduling, result submission, and result validation.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 4, Epic 4.3
"""

from typing import Dict, Any, Optional
from datetime import datetime

from common.events import get_event_bus, Event
from apps.tournament_ops.adapters import (
    TeamAdapter,
    UserAdapter,
    GameAdapter,
    MatchAdapter,
)
from apps.tournament_ops.dtos import MatchDTO
from apps.tournament_ops.exceptions import (
    InvalidMatchStateError,
    MatchLifecycleError,
)


class MatchService:
    """
    Orchestrates match lifecycle and result processing.

    This service manages:
    - Match scheduling and notifications
    - Match result submission and validation
    - Dispute detection and escalation
    - Bracket progression triggers
    - Match event publishing

    Implementation Status:
    - Phase 1, Epic 1.4: Service skeleton ✅
    - Phase 6, Epic 6.1: Result submission workflow (future)
    - Phase 6, Epic 6.2: Dispute resolution integration (future)
    - Phase 8: Stats pipeline integration (future)

    Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 6 (Result Pipeline)
    """

    def __init__(
        self,
        team_adapter: TeamAdapter,
        user_adapter: UserAdapter,
        game_adapter: GameAdapter,
        match_adapter: MatchAdapter,
    ) -> None:
        """
        Initialize match service with required adapters.

        Args:
            team_adapter: Adapter for team data access.
            user_adapter: Adapter for user/profile data access.
            game_adapter: Adapter for game configuration access.
            match_adapter: Adapter for match data access.
        """
        self.team_adapter = team_adapter
        self.user_adapter = user_adapter
        self.game_adapter = game_adapter
        self.match_adapter = match_adapter
        self.event_bus = get_event_bus()

    def schedule_match(
        self, match_id: int, scheduled_time: Optional[datetime] = None
    ) -> MatchDTO:
        """
        Schedule a match and notify teams.

        Workflow:
        1. Validate match exists and is in pending state
        2. Update match scheduled_time
        3. Publish MatchScheduledEvent
        4. Trigger notifications to both teams

        Args:
            match_id: ID of the match to schedule.
            scheduled_time: Optional datetime for match schedule.

        Returns:
            Updated MatchDTO.

        Raises:
            InvalidMatchStateError: If match is not in pending state.

        Reference: Phase 4, Epic 4.3 (Match Lifecycle Management)
        """
        # Method-level import for Match state constants
        from apps.tournaments.models import Match

        # Get current match state
        match = self.match_adapter.get_match(match_id)

        # Validate match is in pending state (scheduled, check_in, ready, cancelled)
        valid_states = ["pending"]
        if match.state not in valid_states:
            raise InvalidMatchStateError(
                f"Cannot schedule match {match_id} with state '{match.state}'. "
                f"Expected one of {valid_states}."
            )

        # Update match to SCHEDULED state with scheduled_time
        updated_match = self.match_adapter.update_match_state(
            match_id=match_id,
            new_state=Match.SCHEDULED,
            scheduled_time=scheduled_time,
        )

        # Publish MatchScheduledEvent
        self.event_bus.publish(
            Event(
                name="MatchScheduledEvent",
                payload={
                    "match_id": match_id,
                    "tournament_id": updated_match.tournament_id,
                    "team_a_id": updated_match.team_a_id,
                    "team_b_id": updated_match.team_b_id,
                    "scheduled_time": scheduled_time.isoformat()
                    if scheduled_time
                    else None,
                    "round_number": updated_match.round_number,
                },
            )
        )

        return updated_match

    def report_match_result(
        self, match_id: int, submitted_by_user_id: int, raw_result_payload: Dict[str, Any]
    ) -> MatchDTO:
        """
        Submit match result from a participant.

        Workflow (Phase 4 scope – no full dispute system yet):
        1. Validate match is in scheduled/live state
        2. Use GameAdapter → GameRulesEngine to validate raw_result_payload
        3. Determine proposed winner/loser and scores using GameRulesEngine
        4. Update match to PENDING_RESULT state with proposed result
        5. Publish MatchResultSubmittedEvent

        Args:
            match_id: ID of the match.
            submitted_by_user_id: ID of the user reporting the result.
            raw_result_payload: Match result data (scores, stats, etc.).

        Returns:
            Updated MatchDTO.

        Raises:
            InvalidMatchStateError: If match is not in scheduled/live state.
            MatchLifecycleError: If result payload validation fails.

        Reference: Phase 4, Epic 4.3 (Match Lifecycle Management)
        """
        # Method-level import for Match state constants
        from apps.tournaments.models import Match

        # Get current match state
        match = self.match_adapter.get_match(match_id)

        # Validate match is in scheduled or live state
        valid_states = ["pending", "in_progress"]
        if match.state not in valid_states:
            raise InvalidMatchStateError(
                f"Cannot report result for match {match_id} with state '{match.state}'. "
                f"Expected one of {valid_states}."
            )

        # Validate result payload schema using GameAdapter
        # NOTE: In Phase 4, we do basic validation. Full game-specific validation
        # will be added in Phase 6 with GameRulesEngine integration
        if not raw_result_payload:
            raise MatchLifecycleError(
                f"Cannot report match result for match {match_id}. "
                "Result payload is empty."
            )

        # Extract basic result data
        winner_id = raw_result_payload.get("winner_id")
        loser_id = raw_result_payload.get("loser_id")
        winner_score = raw_result_payload.get("winner_score", 0)
        loser_score = raw_result_payload.get("loser_score", 0)

        # Validate required fields
        if not winner_id or not loser_id:
            raise MatchLifecycleError(
                f"Result payload must include winner_id and loser_id. Got: {raw_result_payload}"
            )

        # Validate winner/loser are participants
        participants = {match.team_a_id, match.team_b_id}
        if winner_id not in participants or loser_id not in participants:
            raise MatchLifecycleError(
                f"Winner/loser must be match participants. "
                f"Participants: {participants}, Got winner: {winner_id}, loser: {loser_id}"
            )

        if winner_id == loser_id:
            raise MatchLifecycleError("Winner and loser cannot be the same participant")

        # Update match to PENDING_RESULT state (waiting for confirmation in Phase 6)
        updated_match = self.match_adapter.update_match_state(
            match_id=match_id,
            new_state=Match.PENDING_RESULT,
        )

        # Publish MatchResultSubmittedEvent
        self.event_bus.publish(
            Event(
                name="MatchResultSubmittedEvent",
                payload={
                    "match_id": match_id,
                    "tournament_id": updated_match.tournament_id,
                    "submitted_by_user_id": submitted_by_user_id,
                    "winner_id": winner_id,
                    "loser_id": loser_id,
                    "winner_score": winner_score,
                    "loser_score": loser_score,
                    "raw_result": raw_result_payload,
                },
            )
        )

        return updated_match

    def accept_match_result(self, match_id: int, approved_by_user_id: int) -> MatchDTO:
        """
        Manually accept a match result (admin/organizer action or auto-acceptance).

        Workflow:
        1. Validate match is in pending_result state
        2. Get the proposed result (stored during report_match_result)
        3. Finalize the result (set winner_id, loser_id, scores)
        4. Update match state to COMPLETED
        5. Publish MatchCompletedEvent (triggers bracket progression in Phase 3)

        Args:
            match_id: ID of the match to accept.
            approved_by_user_id: ID of user approving the result.

        Returns:
            Updated MatchDTO.

        Raises:
            InvalidMatchStateError: If match is not in pending_result state.

        Reference: Phase 4, Epic 4.3 (Match Lifecycle Management)
        """
        # Method-level import for Match state constants
        from apps.tournaments.models import Match

        # Get current match state
        match = self.match_adapter.get_match(match_id)

        # Validate match is in pending_result state
        valid_states = ["in_progress"]  # DTO state for PENDING_RESULT
        if match.state not in valid_states:
            raise InvalidMatchStateError(
                f"Cannot accept result for match {match_id} with state '{match.state}'. "
                f"Expected one of {valid_states}."
            )

        # In Phase 4, we assume result data is already validated and stored
        # In Phase 6, we'll add full dispute resolution and opponent confirmation
        # For now, we need to extract proposed result from somewhere
        # Since we don't have result storage yet, we'll require result in the match DTO

        if not match.result:
            raise MatchLifecycleError(
                f"Cannot accept match result for match {match_id}. No result data found."
            )

        winner_id = match.result.get("winner_id")
        loser_id = match.result.get("loser_id")
        winner_score = match.result.get("participant1_score", 0)
        loser_score = match.result.get("participant2_score", 0)

        # NOTE: For Phase 4, we'll accept results as-is
        # Phase 6 will add full validation and dispute resolution

        # Update match state to COMPLETED
        updated_match = self.match_adapter.update_match_state(
            match_id=match_id,
            new_state=Match.COMPLETED,
            completed_at=datetime.now(),
        )

        # Publish MatchCompletedEvent (triggers bracket progression)
        self.event_bus.publish(
            Event(
                name="MatchCompletedEvent",
                payload={
                    "match_id": match_id,
                    "tournament_id": updated_match.tournament_id,
                    "winner_id": winner_id,
                    "loser_id": loser_id,
                    "approved_by_user_id": approved_by_user_id,
                    "round_number": updated_match.round_number,
                },
            )
        )

        return updated_match

    def void_match_result(self, match_id: int, reason: str, initiated_by_user_id: int) -> MatchDTO:
        """
        Void a match result and reset match to pending (admin action).

        Workflow:
        1. Validate match has a result (pending_result or completed state)
        2. Reset match state to SCHEDULED
        3. Clear result data (winner_id, loser_id, scores)
        4. Publish MatchVoidedEvent

        Args:
            match_id: ID of the match to void.
            reason: Reason for voiding the result.
            initiated_by_user_id: ID of user initiating the void.

        Returns:
            Updated MatchDTO.

        Raises:
            InvalidMatchStateError: If match has no result to void.

        Reference: Phase 4, Epic 4.3 (Match Lifecycle Management)
        """
        # Method-level import for Match state constants
        from apps.tournaments.models import Match

        # Get current match state
        match = self.match_adapter.get_match(match_id)

        # Validate match has a result to void (pending_result, completed, or disputed)
        voidable_states = ["in_progress", "completed", "disputed"]
        if match.state not in voidable_states:
            raise InvalidMatchStateError(
                f"Cannot void result for match {match_id} with state '{match.state}'. "
                f"Expected one of {voidable_states}."
            )

        # Reset match to SCHEDULED state and clear result fields
        updated_match = self.match_adapter.update_match_state(
            match_id=match_id,
            new_state=Match.SCHEDULED,
            winner_id=None,
            loser_id=None,
            participant1_score=0,
            participant2_score=0,
            completed_at=None,
        )

        # Publish MatchVoidedEvent
        self.event_bus.publish(
            Event(
                name="MatchVoidedEvent",
                payload={
                    "match_id": match_id,
                    "tournament_id": updated_match.tournament_id,
                    "reason": reason,
                    "initiated_by_user_id": initiated_by_user_id,
                    "previous_state": match.state,
                },
            )
        )

        return updated_match
