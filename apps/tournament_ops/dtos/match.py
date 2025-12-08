"""
Match DTOs.

Data Transfer Objects for match-related data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import DTOBase


@dataclass
class MatchDTO(DTOBase):
    """
    DTO for match data.

    Represents a match without coupling to the Django Match ORM model.
    Used by TournamentOps services to work with match information.

    Attributes:
        id: Match primary key.
        tournament_id: ID of the tournament this match belongs to.
        team_a_id: ID of the first team.
        team_b_id: ID of the second team.
        round_number: Round number in the tournament bracket.
        stage: Stage identifier (e.g., "quarterfinals", "semifinals").
        state: Match state (pending, in_progress, completed, disputed).
        scheduled_time: Optional scheduled time for the match.
        result: Optional match result data (scores, winner, etc.).
    """

    id: int
    tournament_id: int
    team_a_id: int
    team_b_id: int
    round_number: int
    stage: str
    state: str  # pending, in_progress, completed, disputed
    scheduled_time: Optional[datetime]
    result: Optional[Dict[str, Any]]

    @classmethod
    def from_model(cls, model: any) -> "MatchDTO":
        """
        Create MatchDTO from a match model.

        Args:
            model: Match model instance or dict.

        Returns:
            MatchDTO instance.
        """
        return cls(
            id=getattr(model, "id", model.get("id") if hasattr(model, "get") else 0),
            tournament_id=getattr(model, "tournament_id", model.get("tournament_id") if hasattr(model, "get") else 0),
            team_a_id=getattr(model, "team_a_id", model.get("team_a_id") if hasattr(model, "get") else 0),
            team_b_id=getattr(model, "team_b_id", model.get("team_b_id") if hasattr(model, "get") else 0),
            round_number=getattr(model, "round_number", model.get("round_number") if hasattr(model, "get") else 1),
            stage=getattr(model, "stage", model.get("stage") if hasattr(model, "get") else ""),
            state=getattr(model, "state", model.get("state") if hasattr(model, "get") else "pending"),
            scheduled_time=getattr(model, "scheduled_time", model.get("scheduled_time") if hasattr(model, "get") else None),
            result=getattr(model, "result", model.get("result") if hasattr(model, "get") else None),
        )

    def validate(self) -> List[str]:
        """
        Validate match data.

        Ensures:
        - round_number > 0
        - team_a_id and team_b_id are different
        - state is a valid value
        - If state is completed, result should exist

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if self.round_number <= 0:
            errors.append("round_number must be positive")

        if self.team_a_id == self.team_b_id:
            errors.append("team_a_id and team_b_id must be different")

        valid_states = {"pending", "in_progress", "completed", "disputed"}
        if self.state not in valid_states:
            errors.append(f"state must be one of {valid_states}")

        if self.state == "completed" and not self.result:
            errors.append("Completed match must have result")

        if not self.stage:
            errors.append("stage cannot be empty")

        return errors
