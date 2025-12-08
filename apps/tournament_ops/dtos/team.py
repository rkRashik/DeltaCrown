"""
Team DTOs.

Data Transfer Objects for team-related data.
"""

from dataclasses import dataclass
from typing import List, Optional

from .base import DTOBase


@dataclass
class TeamDTO(DTOBase):
    """
    DTO for team data.

    Represents a team without coupling to the Django Team ORM model.
    Used by TeamAdapter to return team information to TournamentOps orchestration layer.

    Attributes:
        id: Team primary key.
        name: Team display name.
        captain_id: User ID of the team captain.
        captain_name: Display name of the captain.
        member_ids: List of user IDs for all team members.
        member_names: List of display names for all team members.
        game: Game slug (e.g., "valorant", "csgo") that this team is registered for.
        is_verified: Whether the team has been verified/approved.
        logo_url: Optional URL to the team's logo image.
    """

    id: int
    name: str
    captain_id: int
    captain_name: str
    member_ids: List[int]
    member_names: List[str]
    game: str  # game slug, not model
    is_verified: bool
    logo_url: Optional[str]

    @classmethod
    def from_model(cls, model: any) -> "TeamDTO":
        """
        Create TeamDTO from a team model.

        Args:
            model: Team model instance or dict.

        Returns:
            TeamDTO instance.
        """
        # Extract game slug from model.game or model.game.slug
        game_value = getattr(model, "game", model.get("game") if hasattr(model, "get") else None)
        if game_value:
            game_slug = getattr(game_value, "slug", game_value.get("slug") if hasattr(game_value, "get") else str(game_value))
        else:
            game_slug = ""

        return cls(
            id=getattr(model, "id", model.get("id") if hasattr(model, "get") else 0),
            name=getattr(model, "name", model.get("name") if hasattr(model, "get") else ""),
            captain_id=getattr(model, "captain_id", model.get("captain_id") if hasattr(model, "get") else 0),
            captain_name=getattr(model, "captain_name", model.get("captain_name") if hasattr(model, "get") else ""),
            member_ids=getattr(model, "member_ids", model.get("member_ids") if hasattr(model, "get") else []),
            member_names=getattr(model, "member_names", model.get("member_names") if hasattr(model, "get") else []),
            game=game_slug,
            is_verified=getattr(model, "is_verified", model.get("is_verified") if hasattr(model, "get") else False),
            logo_url=getattr(model, "logo_url", model.get("logo_url") if hasattr(model, "get") else None),
        )

    def validate(self) -> List[str]:
        """
        Validate team data.

        Ensures:
        - name is not empty
        - captain_id is present in member_ids
        - member_ids and member_names have same length
        - game is not empty

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.name:
            errors.append("name cannot be empty")

        if not self.game:
            errors.append("game cannot be empty")

        if self.captain_id not in self.member_ids:
            errors.append("captain_id must be in member_ids")

        if len(self.member_ids) != len(self.member_names):
            errors.append("member_ids and member_names must have same length")

        return errors
