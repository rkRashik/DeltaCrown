"""
Registration DTOs.

Data Transfer Objects for tournament registration data.
"""

from dataclasses import dataclass
from typing import Dict, Any, List

from .base import DTOBase


@dataclass
class RegistrationDTO(DTOBase):
    """
    DTO for tournament registration data.

    Represents a tournament registration without coupling to the Django
    Registration ORM model. Used by TournamentOps services for registration workflows.

    Attributes:
        id: Registration primary key.
        tournament_id: ID of the tournament being registered for.
        team_id: ID of the team registering.
        user_id: ID of the user who initiated registration (usually team captain).
        answers: Custom registration question answers (JSON).
        status: Registration status (pending, approved, rejected, withdrawn).
    """

    id: int
    tournament_id: int
    team_id: int
    user_id: int
    answers: Dict[str, Any]
    status: str  # pending, approved, rejected, withdrawn

    @classmethod
    def from_model(cls, model: any) -> "RegistrationDTO":
        """
        Create RegistrationDTO from a registration model.

        Args:
            model: Registration model instance or dict.

        Returns:
            RegistrationDTO instance.
        """
        return cls(
            id=getattr(model, "id", model.get("id") if hasattr(model, "get") else 0),
            tournament_id=getattr(model, "tournament_id", model.get("tournament_id") if hasattr(model, "get") else 0),
            team_id=getattr(model, "team_id", model.get("team_id") if hasattr(model, "get") else 0),
            user_id=getattr(model, "user_id", model.get("user_id") if hasattr(model, "get") else 0),
            answers=getattr(model, "answers", model.get("answers") if hasattr(model, "get") else {}),
            status=getattr(model, "status", model.get("status") if hasattr(model, "get") else "pending"),
        )

    def validate(self) -> List[str]:
        """
        Validate registration data.

        Ensures:
        - status is a valid value
        - answers is a dict (not None)

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        valid_statuses = {"pending", "approved", "rejected", "withdrawn"}
        if self.status not in valid_statuses:
            errors.append(f"status must be one of {valid_statuses}")

        if self.answers is None:
            errors.append("answers cannot be None (use empty dict)")

        return errors
