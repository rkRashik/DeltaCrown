"""
Stage DTOs.

Data Transfer Objects for tournament stage/bracket data.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

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
        type: Stage type (single_elim, double_elim, swiss, round_robin, etc.).
        order: Execution order of this stage in the tournament.
        config: Stage-specific configuration (JSON).
        metadata: Additional generator-specific metadata (rounds_count, grand_finals_reset, etc.).
    """

    id: int = 0
    name: str = ""
    type: str = "bracket"
    order: int = 1
    config: Dict[str, Any] = None  # type: ignore[assignment]
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}

    @classmethod
    def from_model(cls, model: any) -> "StageDTO":
        """
        Create StageDTO from a stage model.

        Args:
            model: Stage model instance or dict.

        Returns:
            StageDTO instance.
        """
        def _get(attr, default=None):
            return getattr(model, attr, model.get(attr, default) if hasattr(model, "get") else default)

        return cls(
            id=_get("id", 0),
            name=_get("name", ""),
            type=_get("type", "bracket"),
            order=_get("order", 1),
            config=_get("config", {}),
            metadata=_get("metadata"),
        )

    def validate(self) -> List[str]:
        """
        Validate stage data.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.name:
            errors.append("name cannot be empty")

        valid_types = {
            "bracket", "group", "swiss", "round_robin",
            "single_elim", "double_elim",
            "single-elimination", "double-elimination",
            "round-robin",
        }
        if self.type not in valid_types:
            errors.append(f"type must be one of {valid_types}")

        if self.order <= 0:
            errors.append("order must be positive")

        if self.config is None:
            errors.append("config cannot be None (use empty dict)")

        return errors
