"""
Stage DTOs.

Data Transfer Objects for tournament stage/bracket data.
"""

from dataclasses import dataclass
from typing import Dict, Any, List

from .base import DTOBase


@dataclass
class StageDTO(DTOBase):
    """
    DTO for tournament stage data.

    Represents a tournament stage (bracket phase) without coupling to Django models.
    Used by TournamentOps services to work with multi-stage tournament configurations.

    Attributes:
        id: Stage primary key.
        name: Stage display name (e.g., "Group Stage", "Playoffs").
        type: Stage type (bracket, group, swiss, round_robin).
        order: Execution order of this stage in the tournament.
        config: Stage-specific configuration (JSON).
    """

    id: int
    name: str
    type: str  # bracket, group, swiss, round_robin
    order: int
    config: Dict[str, Any]

    @classmethod
    def from_model(cls, model: any) -> "StageDTO":
        """
        Create StageDTO from a stage model.

        Args:
            model: Stage model instance or dict.

        Returns:
            StageDTO instance.
        """
        return cls(
            id=getattr(model, "id", model.get("id") if hasattr(model, "get") else 0),
            name=getattr(model, "name", model.get("name") if hasattr(model, "get") else ""),
            type=getattr(model, "type", model.get("type") if hasattr(model, "get") else "bracket"),
            order=getattr(model, "order", model.get("order") if hasattr(model, "get") else 1),
            config=getattr(model, "config", model.get("config") if hasattr(model, "get") else {}),
        )

    def validate(self) -> List[str]:
        """
        Validate stage data.

        Ensures:
        - name is not empty
        - type is valid
        - order is positive
        - config is not None

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.name:
            errors.append("name cannot be empty")

        valid_types = {"bracket", "group", "swiss", "round_robin"}
        if self.type not in valid_types:
            errors.append(f"type must be one of {valid_types}")

        if self.order <= 0:
            errors.append("order must be positive")

        if self.config is None:
            errors.append("config cannot be None (use empty dict)")

        return errors
