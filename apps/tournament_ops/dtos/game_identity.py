"""
Game identity configuration DTOs.

DTOs for game player identity fields and validation rules.
"""

from dataclasses import dataclass
from typing import Optional, List

from .base import DTOBase


@dataclass
class GamePlayerIdentityConfigDTO(DTOBase):
    """
    DTO for game player identity field configuration.

    Represents the schema for a single identity field (e.g., "riot_id", "steam_id")
    required by a game. Used by GameAdapter to describe what fields are needed
    for player verification.

    Attributes:
        field_name: Internal field name (e.g., "riot_id").
        display_label: Human-readable label for the field.
        validation_pattern: Optional regex pattern for validation.
        is_required: Whether this field is mandatory for the game.
        is_immutable: Whether the field can be changed after initial setup.
        help_text: Guidance text shown to users.
        placeholder: Example value shown in empty input fields.
    """

    field_name: str
    display_label: str
    validation_pattern: Optional[str]
    is_required: bool
    is_immutable: bool
    help_text: str
    placeholder: str

    @classmethod
    def from_model(cls, model: any) -> "GamePlayerIdentityConfigDTO":
        """
        Create GamePlayerIdentityConfigDTO from a config model.

        Args:
            model: Game identity config model instance or dict.

        Returns:
            GamePlayerIdentityConfigDTO instance.
        """
        return cls(
            field_name=getattr(model, "field_name", model.get("field_name") if hasattr(model, "get") else ""),
            display_label=getattr(model, "display_label", model.get("display_label") if hasattr(model, "get") else ""),
            validation_pattern=getattr(model, "validation_pattern", model.get("validation_pattern") if hasattr(model, "get") else None),
            is_required=getattr(model, "is_required", model.get("is_required") if hasattr(model, "get") else False),
            is_immutable=getattr(model, "is_immutable", model.get("is_immutable") if hasattr(model, "get") else False),
            help_text=getattr(model, "help_text", model.get("help_text") if hasattr(model, "get") else ""),
            placeholder=getattr(model, "placeholder", model.get("placeholder") if hasattr(model, "get") else ""),
        )

    def validate(self) -> List[str]:
        """
        Validate game identity config.

        Ensures:
        - field_name is not empty
        - display_label is not empty
        - help_text is not empty

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.field_name:
            errors.append("field_name cannot be empty")

        if not self.display_label:
            errors.append("display_label cannot be empty")

        if not self.help_text:
            errors.append("help_text cannot be empty")

        return errors
