"""
Tournament DTOs.

Data Transfer Objects for tournament-related data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base import DTOBase


@dataclass
class TournamentDTO(DTOBase):
    """
    DTO for tournament data.

    Represents a tournament without coupling to the Django Tournament ORM model.
    Used by TournamentOps services to work with tournament information.

    Attributes:
        id: Tournament primary key.
        name: Tournament display name.
        game_slug: Game identifier (e.g., "valorant", "csgo").
        stage: Current tournament stage/phase.
        team_size: Required number of players per team.
        max_teams: Maximum number of teams allowed.
        status: Tournament status (draft, open, in_progress, completed, cancelled).
        start_time: Scheduled start time for the tournament.
        ruleset: Tournament-specific rules and configuration (JSON).
    """

    id: int
    name: str
    game_slug: str
    stage: str
    team_size: int
    max_teams: int
    status: str
    start_time: datetime
    ruleset: Dict[str, Any]

    @classmethod
    def from_model(cls, model: Any) -> "TournamentDTO":
        """
        Create TournamentDTO from a tournament model instance.

        This method uses duck-typing to extract fields from any object with
        tournament-like attributes. It does not import Django models directly.

        Expected model structure (current apps.tournaments.models.Tournament):
        - id: int
        - name: str
        - game: object with 'slug' attribute (or dict with 'slug' key)
        - stage: str
        - team_size: int
        - max_teams: int
        - status: str
        - start_time: datetime
        - ruleset: dict (or JSON field)

        Args:
            model: Tournament model instance or dict-like object.

        Returns:
            TournamentDTO instance.

        Example:
            # From ORM model (no import needed at call site)
            dto = TournamentDTO.from_model(tournament)

            # From dict
            dto = TournamentDTO.from_model({
                'id': 1,
                'name': 'Summer Cup',
                'game': {'slug': 'valorant'},
                ...
            })
        """
        # Handle game attribute (could be object with slug or dict)
        game = getattr(model, "game", model.get("game") if hasattr(model, "get") else None)
        game_slug = getattr(game, "slug", game.get("slug") if hasattr(game, "get") else str(game))

        return cls(
            id=getattr(model, "id", model.get("id") if hasattr(model, "get") else 0),
            name=getattr(model, "name", model.get("name") if hasattr(model, "get") else ""),
            game_slug=game_slug,
            stage=getattr(model, "stage", model.get("stage") if hasattr(model, "get") else ""),
            team_size=getattr(model, "team_size", model.get("team_size") if hasattr(model, "get") else 0),
            max_teams=getattr(model, "max_teams", model.get("max_teams") if hasattr(model, "get") else 0),
            status=getattr(model, "status", model.get("status") if hasattr(model, "get") else ""),
            start_time=getattr(model, "start_time", model.get("start_time") if hasattr(model, "get") else datetime.utcnow()),
            ruleset=getattr(model, "ruleset", model.get("ruleset") if hasattr(model, "get") else {}),
        )

    def validate(self) -> List[str]:
        """
        Validate tournament data integrity.

        Performs in-memory validation checks without external service calls.

        Returns:
            List of validation error messages (empty if valid).

        Example:
            errors = tournament_dto.validate()
            if errors:
                raise ValueError(f"Invalid tournament: {', '.join(errors)}")
        """
        errors = []

        if self.team_size <= 0:
            errors.append("team_size must be greater than 0")

        if self.max_teams <= 0:
            errors.append("max_teams must be greater than 0")

        if not self.start_time:
            errors.append("start_time is required")

        if not self.name or not self.name.strip():
            errors.append("name cannot be empty")

        if not self.game_slug or not self.game_slug.strip():
            errors.append("game_slug cannot be empty")

        return errors
