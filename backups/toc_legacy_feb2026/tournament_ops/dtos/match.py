"""
Match DTOs.

Data Transfer Objects for match-related data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Dict, List

from .base import DTOBase


@dataclass
class MatchDTO(DTOBase):
    """
    DTO for match data.

    Represents a match without coupling to the Django Match ORM model.
    Used by TournamentOps services to work with match information.

    Core fields:
        id: Match primary key (None before persistence).
        tournament_id: ID of the tournament this match belongs to.
        team_a_id: ID of the first team (None for TBD matches).
        team_b_id: ID of the second team (None for TBD matches).
        round_number: Round number in the tournament bracket.
        stage: Stage label (e.g., "Round 1", "Third Place").
        state: Match state (pending, in_progress, completed, disputed).

    Extended fields (used by bracket generators):
        stage_id: FK to Stage record.
        match_number: Position within a round (1-indexed).
        stage_type: Bracket section (winners, losers, grand_finals, main, third_place).
        team1_name / team2_name: Display names for bracket rendering.
        metadata: Generator-specific extra data (bracket_type, seeding, etc.).
    """

    # --- core ---
    id: Any = None
    tournament_id: int = 0
    team_a_id: Optional[int] = None
    team_b_id: Optional[int] = None
    round_number: int = 1
    stage: str = ""
    state: str = "pending"
    scheduled_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    # --- extended (bracket generators) ---
    stage_id: Optional[int] = None
    match_number: Optional[int] = None
    stage_type: Optional[str] = None
    team1_name: Optional[str] = None
    team2_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_model(cls, model: Any) -> "MatchDTO":
        """
        Create MatchDTO from a match model.

        Args:
            model: Match model instance or dict.

        Returns:
            MatchDTO instance.
        """
        def _get(attr, default=None):
            return getattr(model, attr, model.get(attr, default) if hasattr(model, "get") else default)

        return cls(
            id=_get("id", 0),
            tournament_id=_get("tournament_id", 0),
            team_a_id=_get("team_a_id", 0),
            team_b_id=_get("team_b_id", 0),
            round_number=_get("round_number", 1),
            stage=_get("stage", ""),
            state=_get("state", "pending"),
            scheduled_time=_get("scheduled_time"),
            result=_get("result"),
        )

    def validate(self) -> List[str]:
        """
        Validate match data.

        Ensures:
        - round_number > 0
        - team_a_id and team_b_id are different (when both set)
        - state is a valid value
        - If state is completed, result should exist

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if self.round_number <= 0:
            errors.append("round_number must be positive")

        if (
            self.team_a_id is not None
            and self.team_b_id is not None
            and self.team_a_id == self.team_b_id
        ):
            errors.append("team_a_id and team_b_id must be different")

        valid_states = {"pending", "in_progress", "completed", "disputed"}
        if self.state not in valid_states:
            errors.append(f"state must be one of {valid_states}")

        if self.state == "completed" and not self.result:
            errors.append("Completed match must have result")

        return errors
