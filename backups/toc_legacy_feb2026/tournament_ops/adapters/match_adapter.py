"""
Match adapter for TournamentOps.

Provides match data access without coupling to Match ORM model.
Follows adapter pattern established in Phase 4, Epic 4.1.

Reference: ROADMAP_AND_EPICS_PART_4.md Phase 4, Epic 4.3
"""

from typing import Protocol, Optional
from datetime import datetime

from apps.tournament_ops.dtos import MatchDTO
from apps.tournament_ops.exceptions import MatchNotFoundError


class MatchAdapterProtocol(Protocol):
    """
    Protocol for match data access.

    Defines interface for reading and updating match data without
    direct ORM coupling. Implementations should use method-level imports.
    """

    def get_match(self, match_id: int) -> MatchDTO:
        """
        Get match by ID.

        Args:
            match_id: Match ID to retrieve.

        Returns:
            MatchDTO representing the match.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        ...

    def update_match_state(
        self, match_id: int, new_state: str, **kwargs
    ) -> MatchDTO:
        """
        Update match state and optional fields.

        Args:
            match_id: Match ID to update.
            new_state: New match state (scheduled, live, completed, etc.).
            **kwargs: Optional fields to update (scheduled_time, winner_id, scores, etc.).

        Returns:
            Updated MatchDTO.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        ...

    def update_match_result(
        self,
        match_id: int,
        winner_id: int,
        loser_id: int,
        winner_score: int,
        loser_score: int,
        result_metadata: Optional[dict] = None,
    ) -> MatchDTO:
        """
        Update match with result data.

        Args:
            match_id: Match ID to update.
            winner_id: ID of winning team/participant.
            loser_id: ID of losing team/participant.
            winner_score: Winner's score.
            loser_score: Loser's score.
            result_metadata: Optional metadata (game-specific stats, screenshots, etc.).

        Returns:
            Updated MatchDTO.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        ...


class MatchAdapter:
    """
    Concrete match adapter implementation.

    Uses method-level imports to avoid ORM in tournament_ops.
    Converts Match model instances to MatchDTO.
    """

    def get_match(self, match_id: int) -> MatchDTO:
        """
        Get match by ID.

        Args:
            match_id: Match ID to retrieve.

        Returns:
            MatchDTO representing the match.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        # Method-level import to avoid ORM in tournament_ops
        from apps.tournaments.models import Match

        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise MatchNotFoundError(f"Match with ID {match_id} not found")

        return self._convert_to_dto(match)

    def update_match_state(
        self, match_id: int, new_state: str, **kwargs
    ) -> MatchDTO:
        """
        Update match state and optional fields.

        Args:
            match_id: Match ID to update.
            new_state: New match state.
            **kwargs: Optional fields (scheduled_time, started_at, completed_at, etc.).

        Returns:
            Updated MatchDTO.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        from apps.tournaments.models import Match

        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise MatchNotFoundError(f"Match with ID {match_id} not found")

        # Update state
        match.state = new_state

        # Update optional fields
        for key, value in kwargs.items():
            if hasattr(match, key):
                setattr(match, key, value)

        match.save()
        return self._convert_to_dto(match)

    def update_match_result(
        self,
        match_id: int,
        winner_id: int,
        loser_id: int,
        winner_score: int,
        loser_score: int,
        result_metadata: Optional[dict] = None,
    ) -> MatchDTO:
        """
        Update match with result data.

        Args:
            match_id: Match ID to update.
            winner_id: ID of winning team/participant.
            loser_id: ID of losing team/participant.
            winner_score: Winner's score.
            loser_score: Loser's score.
            result_metadata: Optional metadata.

        Returns:
            Updated MatchDTO.

        Raises:
            MatchNotFoundError: If match doesn't exist.
        """
        from apps.tournaments.models import Match

        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            raise MatchNotFoundError(f"Match with ID {match_id} not found")

        # Update result fields
        match.winner_id = winner_id
        match.loser_id = loser_id

        # Set scores based on winner/loser
        if winner_id == match.participant1_id:
            match.participant1_score = winner_score
            match.participant2_score = loser_score
        else:
            match.participant1_score = loser_score
            match.participant2_score = winner_score

        # Store metadata if provided
        if result_metadata:
            match.lobby_info = {**match.lobby_info, "result_metadata": result_metadata}

        match.save()
        return self._convert_to_dto(match)

    def _convert_to_dto(self, match) -> MatchDTO:
        """
        Convert Match model to MatchDTO.

        Args:
            match: Match model instance.

        Returns:
            MatchDTO.
        """
        return MatchDTO(
            id=match.id,
            tournament_id=match.tournament_id,
            team_a_id=match.participant1_id or 0,
            team_b_id=match.participant2_id or 0,
            round_number=match.round_number,
            stage=f"round_{match.round_number}",  # Simple stage identifier
            state=self._map_state(match.state),
            scheduled_time=match.scheduled_time,
            result={
                "winner_id": match.winner_id,
                "loser_id": match.loser_id,
                "participant1_score": match.participant1_score,
                "participant2_score": match.participant2_score,
                "lobby_info": match.lobby_info,
            }
            if match.state == "completed"
            else None,
        )

    def _map_state(self, orm_state: str) -> str:
        """
        Map ORM match state to DTO state.

        Args:
            orm_state: Match model state.

        Returns:
            DTO state string.
        """
        # Match model states: scheduled, check_in, ready, live, pending_result, completed, disputed, forfeit, cancelled
        # DTO states: pending, in_progress, completed, disputed
        state_map = {
            "scheduled": "pending",
            "check_in": "pending",
            "ready": "pending",
            "live": "in_progress",
            "pending_result": "in_progress",
            "completed": "completed",
            "disputed": "disputed",
            "forfeit": "completed",
            "cancelled": "pending",
        }
        return state_map.get(orm_state, "pending")
